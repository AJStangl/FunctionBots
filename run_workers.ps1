function RunBot
{
    venv/Scripts/activate
    func start --functions function-queue-submission-worker function-queue-text-generation-worker-1 function-queue-text-generation-worker-2 function-queue-text-generation-worker-3 -p 7006 --verbose
}

while(1) {
    RunBot
}