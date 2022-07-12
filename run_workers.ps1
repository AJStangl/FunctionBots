function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-text-generation-worker-1 function-queue-text-generation-worker-2 function-queue-text-generation-worker-3 --verbose --port 7079
}

while(1) {
    RunBot
}