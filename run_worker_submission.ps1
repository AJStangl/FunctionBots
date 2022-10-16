function RunBot
{
    venv/Scripts/activate
    func start --functions function-queue-submission-worker -p 7014 --verbose
}

while(1) {
    RunBot
}