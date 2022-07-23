function RunBot
{
    .\venv\Scripts\activate.ps1
    func start -p 7000 --verbose
}

while(1) {
    RunBot
}