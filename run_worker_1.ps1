function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-text-generation-worker-1 --verbose --port 7076
}

while(1) {
    RunBot
}

