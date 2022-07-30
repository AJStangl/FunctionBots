function RunBot
{
     conda activate reddit-function-bot
    func start --functions function-queue-reply --verbose
}

while(1) {
    RunBot
}