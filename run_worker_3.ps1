function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-text-generation-worker-3 --verbose --port 7078
}

while(1) {
    RunBot
}