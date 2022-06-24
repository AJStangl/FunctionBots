function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-text-generation-worker-3  --port 7093
}

while(1) {
    RunBot
}