function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-poll-bots function-queue-run --verbose --port 7071
}

while(1) {
    RunBot
}