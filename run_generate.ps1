function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-text-generation-worker-1 function-timer-text-generation-worker-2 function-timer-text-generation-worker-3 --port 7074
}

while(1) {
    RunBot
}

