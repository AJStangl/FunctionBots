function RunBot
{
     conda activate reddit-function-bot
    func start -p 7000 --verbose
}

while(1) {
    RunBot
}