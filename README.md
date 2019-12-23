# Forest backend for Qiskit

Allows running [Qiskit](https://qiskit.org/) code on [Rigetti](https://www.rigetti.com/) simulators and quantum computers by changing only two lines of your Qiskit code.

**More goodies at** [https://quantastica.com](https://quantastica.com)


# Install

```
pip install quantastica-qiskit-forest
```

# Usage

Import `ForestBackend` into your Qiskit code:

```
from quantastica.qiskit_forest import ForestBackend
```

And replace `Aer.get_backend` with `ForestBackend.get_backend`.


# Example

```python
from qiskit import QuantumRegister, ClassicalRegister
from qiskit import QuantumCircuit, execute, Aer

# Import ForestBackend:
from quantastica.qiskit_forest import ForestBackend

qc = QuantumCircuit()

q = QuantumRegister(2, "q")
c = ClassicalRegister(2, "c")

qc.add_register(q)
qc.add_register(c)

qc.h(q[0])
qc.cx(q[0], q[1])

qc.measure(q[0], c[0])
qc.measure(q[1], c[1])


# Instead:
#backend = Aer.get_backend("qasm_simulator")

# Use:
backend = ForestBackend.get_backend("qasm_simulator")

# OR:
# backend = ForestBackend.get_backend("statevector_simulator")
# backend = ForestBackend.get_backend("Aspen-7-28Q-A")
# backend = ForestBackend.get_backend("Aspen-7-28Q-A", as_qvm=True)
# ...

job = execute(qc, backend=backend)
job_result = job.result()

print(job_result.get_counts(qc))

```

# Prerequisites

## Running on your local Rigetti simulator

You need to install [Rigetti Forest SDK](https://qcs.rigetti.com/sdk-downloads) and make sure that `quilc` compiler and `qvm` simulator are running:

Open new terminal and run:

```
quilc -S
```

And in one more new terminal run:

```
qvm -S -c
```

## Running on Rigetti quantum computer

- You need to get access to Rigetti [Quantum Cloud Services](https://qcs.rigetti.com/request-access) (QCS)

- In your Quantum Machine Image (QMI) install this package and Qiskit

- Reserve a [QPU lattice](https://www.rigetti.com/qcs/docs/reservations)

- Run your code via QMI terminal or Jupyter notebook served by your QMI


# Details

**Syntax**

`ForestBackend.get_backend(backend_name = None, as_qvm = False)`


**Arguments**

`backend_name` can be:

- any valid Rigetti lattice name

OR:

- `qasm_simulator` will be sent to QVM as `Nq-qvm` (where `N` is number of qubits in the circuit)

- `statevector_simulator` will be executed as `WavefunctionSimulator.wavefunction()`

If backend name is not provided then it will act as `qasm_simulator`

`as_qvm` boolean:

- `False` (default)

- `True`: if backend_name is QPU lattice name, then code will execute on QVM which will mimic QPU


That's it. Enjoy! :)
