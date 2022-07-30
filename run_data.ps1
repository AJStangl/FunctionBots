function RunBot
{
    .\venv\Scripts\activate.ps1
    func start --functions function-queue-query function-timer-start function-timer-submission-start -p 7010 --verbose
}

while(1) {
    RunBot
}