import meshtastic
import meshtastic.tcp_interface
import meshtastic.__main__
from statemachine import StateMachine, State
from time import sleep


IPv4 = "192.168.0.254"
LONG_NAME = "!deadbeef"
CONFIGS = {
    'lora': {
        'hop_limit': (3, None),
        'tx_power': (30, None),
    },
    'mqtt': {
        'username': ('username', None),
    },
}


class NodeSetConfigStateMachine(StateMachine):
    getConfig = State('getConfig', initial=True)
    checkConfig = State('checkConfig')
    setConfig = State('setConfig')
    finalState = State('finalState', final=True)
    
    true = getConfig.to(checkConfig) | checkConfig.to(finalState) | setConfig.to(getConfig)
    false = getConfig.to.itself() | checkConfig.to(setConfig) | setConfig.to.itself()

    def __init__(self, iface, long_name="!DEADBEEF", configs={}):
        self.iface = iface
        self.long_name = long_name
        self.node = None
        self.configs = configs


        super().__init__()

    def log(self, state, msg):
        print(f'[{self.__class__.__qualname__}] <{state}> {msg}')

    def sleep(self, seconds):
        self.log("", f"Sleeping for {seconds} seconds")
        sleep(seconds)

    def on_enter_getConfig(self):
        self.log("getConfig", f"Getting config for {self.long_name}")

        try:
            self.node = self.iface.getNode(self.long_name, requestChannels=False, timeout=5)

        except Exception as e:
            self.log("getConfig", f"Failed to get node: {e}")
            self.false()
            return
        
        for module, values in self.configs.items():
            self.log("getConfig", f"Requesting {module} config")

            try:
                if module in self.node.localConfig.DESCRIPTOR.fields_by_name:
                    self.node.requestConfig(self.node.localConfig.DESCRIPTOR.fields_by_name.get(module))
                if module in self.node.moduleConfig.DESCRIPTOR.fields_by_name:
                    self.node.requestConfig(self.node.moduleConfig.DESCRIPTOR.fields_by_name.get(module))

            except Exception as e:
                self.log("getConfig", f"Failed to request config: {e}")
                self.false()
                return

            self.sleep(10)
            
            if module in self.node.localConfig.DESCRIPTOR.fields_by_name:
                self.node.waitForConfig(attribute="localConfig")
            if module in self.node.moduleConfig.DESCRIPTOR.fields_by_name:
                self.node.waitForConfig(attribute="moduleConfig")

            for attribute, config_pair in values.items():
                if module in self.node.localConfig.DESCRIPTOR.fields_by_name:
                    self.configs[module][attribute] = (config_pair[0], self.node.localConfig.__getattribute__(module).__getattribute__(attribute))
                if module in self.node.moduleConfig.DESCRIPTOR.fields_by_name:
                    self.configs[module][attribute] = (config_pair[0], self.node.moduleConfig.__getattribute__(module).__getattribute__(attribute))

        for module, values in self.configs.items():
            self.log("getConfig", f"{module}:")
            for attribute, config_pair in values.items():
                self.log("getConfig", f" {attribute}: {config_pair}")

        for module, values in self.configs.items():
            for _, config_pair in values.items():
                if config_pair[1] is None:
                    self.log("getConfig", "Failed to get config")
                    self.false()
                    return
    
        self.log("getConfig", "Successfully got config")
        self.true()


    def on_enter_checkConfig(self):
        self.log("checkConfig", f"Comparing wanted config with current config")
        for module, values in self.configs.items():
            for attribute, config_pair in values.items():
                if config_pair[0] != config_pair[1]:
                    self.log("checkConfig", f"{module}.{attribute} is not equal")
                    self.set_config = config_pair[0]
                    self.false()
                    return
        self.true()

    def on_enter_setConfig(self):
        self.log("setConfig", "Setting config")
        for module, values in self.configs.items():
            for attribute, config_pair in values.items():
                if config_pair[0] != config_pair[1]:
                    self.log("setConfig", f"Setting {module}.{attribute} to {config_pair[0]}")
                    if module in self.node.localConfig.DESCRIPTOR.fields_by_name:
                        self.node.localConfig.__getattribute__(module).__setattr__(attribute, config_pair[0])
                    if module in self.node.moduleConfig.DESCRIPTOR.fields_by_name:
                        self.node.moduleConfig.__getattribute__(module).__setattr__(attribute, config_pair[0])

        self.node.beginSettingsTransaction()
        for module, values in self.configs.items():
            self.node.writeConfig(module)
        self.log("setConfig", "Committing settings transaction")
        self.node.commitSettingsTransaction()
        self.sleep(30)
        self.true()


    def on_enter_finalState(self):
        self.log("finalState", "Finished")



if __name__ == "__main__":
    iface = meshtastic.tcp_interface.TCPInterface(hostname=IPv4)

    nsm = NodeSetConfigStateMachine(iface, LONG_NAME, CONFIGS)
