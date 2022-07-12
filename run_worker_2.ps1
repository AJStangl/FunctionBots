function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-text-generation-worker-2 --verbose --port 7077
}

while(1) {
    RunBot
}