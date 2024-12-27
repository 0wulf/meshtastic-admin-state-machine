# Meshtastic Admin State Machine - Efficiently Manage Node Configurations via the Admin Module

Starting from version 2.5 of the Meshtastic firmware, nodes can be remotely managed via a secure admin module. Prior to this release, configuration changes were made through an insecure admin channel, which had several flaws.

While the new admin module improves security, it introduces certain challenges. For example, not all tasks can be fully acknowledged. Consider the action of changing the device configuration: when this operation is performed, the python API typically receives an **Implicit ACK**, indicating that the packet has been rebroadcast by another node and entered the mesh. However, this does not guarantee secure delivery. The packet may be lost if its time-to-live (TTL or remaining hops) expires, or if the channel is congested.

To address these limitations, I have developed a **Proof of Concept** script that implements a State Machine. This solution ensures that configuration changes are applied successfully by handling these caveats.

## The State Machine Protocol

The State Machine can be described as a **Deterministic Finite Automaton** (DFA) represented as:

$$ A = (Q, \Sigma, q_{\text{getConfig}}, \delta, F) $$

Where:
- $Q = {q\_{\text{getConfig}}, q\_{\text{checkConfig}}, q\_{\text{setConfig}}, q\_f}$ is the set of states,
- $\Sigma = {\text{true}, \text{false}}$ is the finite alphabet,
- $q\_{\text{getConfig}}$ is the initial state,
- $\delta$ is the transition function defined as:
  - $\ \delta(q_{\text{getConfig}}, \text{true}) = q_{\text{checkConfig}} \$
  - $\ \delta(q_{\text{getConfig}}, \text{false}) = q_{\text{getConfig}} \$
  - $\ \delta(q_{\text{checkConfig}}, \text{true}) = q_f \$
  - $\ \delta(q_{\text{checkConfig}}, \text{false}) = q_{\text{setConfig}} \$
  - $\ \delta(q_{\text{setConfig}}, \text{true}) = q_{\text{checkConfig}} \$
  - $\ \delta(q_{\text{setConfig}}, \text{false}) = q_{\text{setConfig}} \$
- $F = {q_f}$ is the set of final states.

![imagen](https://github.com/user-attachments/assets/1be98e19-dd8d-4a67-9eba-f893bd978220)


### How the State Machine Works

The state machine operates based on conditions that occur (or do not occur) at each step. The states and conditions are as follows:

1. $q\_{\text{getConfig}}$: The condition here is to check if the current configuration matches the desired one. If it does, the process ends; if not, the machine moves to the next state.

2. $q\_{\text{checkConfig}}$: In this state, the machine checks whether the configuration was successfully applied. If the configuration is correct, it transitions to the final state, $q_f$. If not, it moves to the **setConfig** state to reapply the changes.

3. $q\_{\text{setConfig}}$: This state deals with sending the configuration change request. The machine waits for an implicit acknowledgment (ACK) to confirm the change has been attempted. If the ACK is received, it transitions back to **checkConfig**. If no ACK is received, it stays in **setConfig** and retries the request.

### Protocol Workflow

The protocol follows a simple flow:

1. **Retrieve the current configuration**: The script starts by fetching the node's current configuration.
2. **Check for configuration differences**: If the current configuration matches the desired settings, the program exits.
3. **Request configuration changes**: If changes are needed, the node is asked to update its configuration.
4. **Verify the change**: After the update request, the machine checks whether the configuration has been successfully applied.
5. **Retry if needed**: If the change was not successfully applied, the script reverts to the previous step and requests the configuration change again.
6. **End the process**: Once the configuration change is confirmed, the process ends.

This state machine provides a robust mechanism for ensuring that configuration changes are successfully applied, overcoming the challenges posed by the presence of implicit ACKs.

## Usage
First create a virtual environment and install the required packages:

```bash
python -m venv .
bin/pip install -r requirements.txt
```

Then, modify the configuration in `main.py` to match your desired settings. Finally, run the script:

```bash
bin/python main.py
```

Be careful when using this script, as it will attempt to change the configuration of the node. Make sure you understand the implications of the changes you are making and remember that some firmware versions are flawed and in some cases you may be resetting the node's radio band configuration.
