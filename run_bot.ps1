function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-poll-bots function-queue-to-content function-timer-table-collection function-timer-submit-post --verbose --port 7070
}

while(1) {
    RunBot
}