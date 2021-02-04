from MainApp.MainApp import MainApp

if __name__ == '__main__':

    app = None
    print("[App] Booting Main App.")
    app = MainApp()
    app.Setup()
    app.Run()

