function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-reply --verbose --port 7074
}

while(1) {
    RunBot
}