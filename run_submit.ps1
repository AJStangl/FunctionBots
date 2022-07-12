function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-submission-start function-queue-submission-worker --verbose --port 7075
}

while(1) {
    RunBot
}