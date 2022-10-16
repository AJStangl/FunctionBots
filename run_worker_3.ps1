function RunBot
{
    venv/Scripts/activate
    func start --functions function-queue-text-generation-worker-3 -p 7013 --verbose
}

while(1) {
    RunBot
}