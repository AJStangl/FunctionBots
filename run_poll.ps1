function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-poll function-queue-reply -p 7005 --verbose
}

while(1) {
    RunBot
}