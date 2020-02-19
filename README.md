On windows use Visual Studio to compile, for Linux there is a makefile.
Binaries will be in the x64 folder.

ORIGINAL TASK:
*   General requirements  
    *   Have to compile and run on Linux (and Windows)
    *   Solution in git
*   Task 1  
    *   Sensor data is sent over UDP and broadcasted to port 12345. There are multiple sensors which send data at random intervals.
    *   Data format: uint8 sensor number, uint8 value type, uint64 reading → payload length: 10B
        *   Possible values for **value type** are defined in sensor\_sender.py:14:28
    *   Log the data from sensors and save it in csv format: timestamp, senor id, sensor reading
    *   Print sensor data to standard output with frequency of 1 Hz, averaging over last 10 values
    *   Sensor data can be requested by sending a UDP packet to port 12346  
        *   **request:** uint8 sensor number, uint8 value type/kind (0 - last value, 1 - mean of last 10 values, 2 - mean of all values) → request length 2B
        *   **response**: uint8 sensor number, uint8 value type, uint64 reading → response length 10B
