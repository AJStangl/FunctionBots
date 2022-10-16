function RunBot
{
    venv/Scripts/activate
    func start --functions function-queue-text-generation-worker-1 -p 7011 --verbose
}

while(1) {
    RunBot
}