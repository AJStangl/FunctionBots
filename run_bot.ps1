function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-run function-timer-start-poll function-timer-submit-post --port 7071
}

while(1) {
    RunBot
}