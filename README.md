# Glasses PubSub System

## Prerequisites

- **Docker** installed
- **Python 3.12** with `pyenv` or similar.
- **Redis**.
- **Visual Studio Code**.

## Setup

1. **Clone the Repository**
    ```bash
    git clone https://github.com/emingenc/even_glasses_redis_control.git
    cd even_glasses_redis_control
    ```

2. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## Running the System

### 1. Start Redis Server

Open a terminal and run:
```bash
docker run --name g1-redis-server -p 6379:6379 -d redis

```

### 2. Run glasses_pubsub.py

Open a terminal and run:
```bash
python glasses_pubsub.py
```

### 3. Run notification_receiver.py

Open a terminal and run:
```bash
python notification_receiver.py
```

### 4. Test with test_command_sender.ipynb

Open the Jupyter Notebook and run the cells.
