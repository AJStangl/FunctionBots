function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-poll function-timer-pending function-timer-comment function-queue-reply function-timer-submission -p 7005 --verbose
}

while(1) {
    RunBot
}