function RunBot
{
    conda activate reddit-function-bot
    func start -p 7000
}

while(1) {
    RunBot
}