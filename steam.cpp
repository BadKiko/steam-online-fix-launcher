#include <iostream>
#include <thread>
#include <chrono>

int main() {
    // Бесконечный цикл для эмуляции работы
    while (true) {
        std::cout << "Running fake steam.exe" << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }

    return 0;
}

