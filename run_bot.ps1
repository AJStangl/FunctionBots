function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-run function-timer-start-poll --verbose --port 7071
}

while(1) {
    RunBot
}