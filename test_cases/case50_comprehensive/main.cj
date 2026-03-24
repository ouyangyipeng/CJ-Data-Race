// case50: 综合测试
// 测试多种并发模式混合使用

main() {
    var counter: Int64 = 0
    var flag: Bool = false
    let mutex = Mutex()
    let channel = Channel<Int64>(10)
    
    // 线程1: 使用Mutex保护
    spawn {
        mutex.lock()
        counter = counter + 1
        mutex.unlock()
    }
    
    // 线程2: 使用Channel通信
    spawn {
        channel.send(100)
    }
    
    // 线程3: 混合使用
    spawn {
        mutex.lock()
        counter = counter + 1
        mutex.unlock()
        channel.send(200)
        flag = true
    }
    
    // 线程4: 读取操作
    spawn {
        let value = channel.receive()
        mutex.lock()
        counter = counter + value
        mutex.unlock()
    }
}