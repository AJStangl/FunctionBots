function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-submit-post function-queue-submission-worker --verbose --port 8010
}

while(1) {
    RunBot
}