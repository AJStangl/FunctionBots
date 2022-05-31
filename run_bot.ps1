function RunBot
{
    conda activate reddit-function-bot
    func start --functions start function-queue-to-content function-timer-poll-bots function-timer-reply function-timer-submit-post function-timer-table-collection --verbose
}

while(1) {
    RunBot
}
