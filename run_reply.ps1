function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-reply --verbose --port 8009
}

while(1) {
    RunBot
}