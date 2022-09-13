function RunBot
{
    venv/Scripts/activate
    func start -p 7000 --verbose
}

while(1) {
    RunBot
}