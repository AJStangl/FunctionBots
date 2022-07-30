function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-worker-1 function-queue-worker-2 function-queue-worker-3 -p 7006 --verbose
}

while(1) {
    RunBot
}