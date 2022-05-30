function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-text-generation-worker-1 function-timer-text-generation-worker-2 function-timer-text-generation-worker-3  function-timer-text-generation-worker-4 function-timer-text-generation-worker-5 function-timer-text-generation-worker-6 --port 7074
}

RunBot
if (!$LASTEXITCODE) {
    RunBot
}

