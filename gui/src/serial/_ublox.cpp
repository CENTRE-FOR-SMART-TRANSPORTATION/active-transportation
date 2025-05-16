#include <iostream>
#include <boost/asio.hpp>
#include <boost/thread.hpp>
#include <queue>
#include <mutex>
#include <condition_variable>

class SerialReader
{
public:
    SerialReader(const std::string &port, unsigned int baud_rate)
        : io_service(), serial(io_service, port), running(true)
    {
        serial.set_option(boost::asio::serial_port_base::baud_rate(baud_rate));
    }

    void start()
    {
        read_thread = boost::thread(&SerialReader::read_raw, this);
    }

    void stop()
    {
        running = false;
        if (read_thread.joinable())
        {
            read_thread.join();
        }
    }

    std::queue<std::vector<uint8_t>> get_parsed_data()
    {
        std::lock_guard<std::mutex> lock(mutex);
        std::queue<std::vector<uint8_t>> data_copy = parsed_data;
        while (!parsed_data.empty())
        {
            parsed_data.pop();
        }
        return data_copy;
    }

private:
    void read_raw()
    {
        while (running)
        {
            try
            {
                if (serial.is_open())
                {
                    std::vector<uint8_t> buffer(256); // Adjust size as needed
                    boost::asio::read(serial, boost::asio::buffer(buffer));

                    // Here you would parse the raw data into UBX packets
                    // For demonstration, we will just push the raw data
                    {
                        std::lock_guard<std::mutex> lock(mutex);
                        parsed_data.push(buffer);
                    }
                }
            }
            catch (const std::exception &e)
            {
                std::cerr << "GPS Read Error: " << e.what() << std::endl;
            }
        }
    }

    boost::asio::io_service io_service;
    boost::asio::serial_port serial;
    boost::thread read_thread;
    bool running;
    std::queue<std::vector<uint8_t>> parsed_data;
    std::mutex mutex;
};

int main()
{
    SerialReader reader("/dev/ttyACM1", 115200); // Adjust port and baud rate as needed
    reader.start();

    // Simulate processing data
    for (int i = 0; i < 10; ++i)
    {
        boost::this_thread::sleep_for(boost::chrono::seconds(1));
        auto packets = reader.get_parsed_data();
        while (!packets.empty())
        {
            // Process each packet
            std::vector<uint8_t> packet = packets.front();
            packets.pop();
            // Here you would parse the UBX packet
            std::cout << "Received packet of size: " << packet.size() << std::endl;
        }
    }

    reader.stop();
    return 0;
}
