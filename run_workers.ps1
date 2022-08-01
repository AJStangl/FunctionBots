function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-queue-worker-1 -p 7006 --verbose
}

while(1) {
    RunBot
}