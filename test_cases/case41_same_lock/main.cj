// case41: 同一锁保护多个变量测试
// 测试一个Mutex保护多个变量的场景（无竞争）

main() {
    var counter1: Int64 = 0
    var counter2: Int64 = 0
    let mutex = Mutex()
    
    spawn {
        mutex.lock()
        counter1 = counter1 + 1
        counter2 = counter2 + 1
        mutex.unlock()
    }
    
    spawn {
        mutex.lock()
        counter1 = counter1 + 2
        counter2 = counter2 + 2
        mutex.unlock()
    }
}