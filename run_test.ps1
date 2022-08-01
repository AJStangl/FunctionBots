function RunBot
{
     conda activate reddit-function-bot
    func start --functions function-queue-reply --verbose -p 7002
}

while(1) {
    RunBot
}