function RunBot
{
    .\venv\Scripts\activate.ps1
    func start --functions function-queue-poll function-queue-query function-queue-reply function-timer-start function-timer-submission-start -p 7005 --verbose
}

while(1) {
    RunBot
}