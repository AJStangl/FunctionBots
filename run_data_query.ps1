function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-query --verbose --port 8002
}

while(1) {
    RunBot
}