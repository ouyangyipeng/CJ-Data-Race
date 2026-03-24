// 测试用例19: 可重入锁保护
// 测试同一个线程多次获取同一把锁的情况

main() {
    var counter: Int64 = 0
    let mutex = Mutex()
    
    // 线程1: 可重入锁保护
    spawn {
        mutex.lock()
        mutex.lock()  // 可重入
        counter = counter + 1
        mutex.unlock()
        mutex.unlock()
    }
    
    // 线程2: 同一把锁保护
    spawn {
        mutex.lock()
        counter = counter + 1
        mutex.unlock()
    }
    
    println(counter)
}