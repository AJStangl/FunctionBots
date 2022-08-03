function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-query function-timer-start function-timer-submission-start -p 7010 --verbose
}

while(1) {
    RunBot
}