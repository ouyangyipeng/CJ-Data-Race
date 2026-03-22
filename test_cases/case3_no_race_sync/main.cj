// 测试用例3: 无竞争 - 使用mutex保护
// 使用互斥锁保护共享变量

main() {
    var counter: Int64 = 0
    let mutex = Mutex()
    
    // 线程1: 使用mutex保护
    spawn {
        mutex.lock()
        counter = counter + 1  // 写操作，受保护
        mutex.unlock()
    }
    
    // 线程2: 使用mutex保护
    spawn {
        mutex.lock()
        counter = counter + 1  // 写操作，受保护
        mutex.unlock()
    }
    
    println(counter)
}