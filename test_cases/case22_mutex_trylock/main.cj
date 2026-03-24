// 测试用例22: tryLock保护
// 测试使用tryLock进行同步保护

main() {
    var counter: Int64 = 0
    let mutex = Mutex()
    
    // 线程1: 使用tryLock保护
    spawn {
        if (mutex.tryLock()) {
            counter = counter + 1  // 写操作，受保护
            mutex.unlock()
        }
    }
    
    // 线程2: 使用tryLock保护
    spawn {
        if (mutex.tryLock()) {
            counter = counter + 1  // 写操作，受保护
            mutex.unlock()
        }
    }
    
    println(counter)
}