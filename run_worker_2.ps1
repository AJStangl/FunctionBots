function RunBot
{
    venv/Scripts/activate
    func start --functions function-queue-text-generation-worker-2 -p 7012 --verbose
}

while(1) {
    RunBot
}