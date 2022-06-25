function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-text-generation-worker-2  --port 7092
}

while(1) {
    RunBot
}