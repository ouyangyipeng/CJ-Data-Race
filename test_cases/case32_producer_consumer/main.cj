// case32: 生产者消费者模式测试
// 测试通过Channel通信的生产者消费者模式

main() {
    let channel = Channel<Int64>(10)
    var produced: Int64 = 0
    var consumed: Int64 = 0
    
    // 生产者
    spawn {
        for (i in 0..10) {
            channel.send(i)
            produced = produced + 1
        }
    }
    
    // 消费者
    spawn {
        for (i in 0..10) {
            let value = channel.receive()
            consumed = consumed + 1
        }
    }
}