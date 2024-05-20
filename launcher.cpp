#include <iostream>
#include <thread>
#include <chrono>
#include <windows.h>

void printHelp(const char* programName) {
    std::cout << "Usage: " << programName << " <game_exe>" << std::endl;
    std::cout << "Example: " << programName << " game.exe" << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printHelp(argv[0]);
        std::this_thread::sleep_for(std::chrono::seconds(5));
        return 1;
    }

    // Константа для пути к steam.exe
    const std::string steamPath = "steam.exe";
    // Получаем имя файла игры из аргумента командной строки
    std::string gamePath = argv[1];

    // Настраиваем структуру STARTUPINFO и PROCESS_INFORMATION для steam.exe
    STARTUPINFO siSteam;
    PROCESS_INFORMATION piSteam;
    ZeroMemory(&siSteam, sizeof(siSteam));
    siSteam.cb = sizeof(siSteam);
    ZeroMemory(&piSteam, sizeof(piSteam));

    // Настраиваем структуру STARTUPINFO и PROCESS_INFORMATION для game.exe
    STARTUPINFO siGame;
    PROCESS_INFORMATION piGame;
    ZeroMemory(&siGame, sizeof(siGame));
    siGame.cb = sizeof(siGame);
    ZeroMemory(&piGame, sizeof(piGame));

    for (int i = 0; i < 100; ++i) {
        // Запускаем steam.exe
        if (!CreateProcess(NULL, const_cast<char*>(steamPath.c_str()), NULL, NULL, FALSE, 0, NULL, NULL, &siSteam, &piSteam)) {
            std::cerr << "Failed to start steam.exe. Error: " << GetLastError() << std::endl;
            return 1;
        }

        // Закрываем дескрипторы процесса и потока для steam.exe
        CloseHandle(piSteam.hProcess);
        CloseHandle(piSteam.hThread);

        // На 50-й итерации запускаем game.exe
        if (i == 49) {
            if (!CreateProcess(NULL, const_cast<char*>(gamePath.c_str()), NULL, NULL, FALSE, 0, NULL, NULL, &siGame, &piGame)) {
                std::cerr << "Failed to start game.exe. Error: " << GetLastError() << std::endl;
                return 1;
            }

            // Закрываем дескрипторы процесса и потока для game.exe
            CloseHandle(piGame.hProcess);
            CloseHandle(piGame.hThread);
        }

        // Задержка 100 миллисекунд перед следующей итерацией
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    return 0;
}

