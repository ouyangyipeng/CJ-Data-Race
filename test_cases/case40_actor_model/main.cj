// case40: Actor模型测试
// 测试Actor模式中的消息传递（无竞争）

class CounterActor {
    private var count: Int64 = 0
    private let mailbox = Channel<Int64>(10)
    
    public func start() {
        spawn {
            loop {
                let msg = mailbox.receive()
                count = count + msg
            }
        }
    }
    
    public func increment(by: Int64) {
        mailbox.send(by)
    }
    
    public func getCount(): Int64 {
        return count
    }
}

main() {
    let actor = CounterActor()
    actor.start()
    
    actor.increment(1)
    actor.increment(2)
    actor.increment(3)
}