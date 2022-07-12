function RunBot
{
    func start --functions function-timer-start function-queue-poll --verbose --port 7072
}

while(1) {
    conda activate reddit-function-bot
    RunBot
}