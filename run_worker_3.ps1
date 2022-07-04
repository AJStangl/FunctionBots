function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-submit-post function-queue-text-generation-worker-3 --verbose --port 7093
}

while(1) {
    RunBot
}