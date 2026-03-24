// case47: 死锁风险测试
// 测试不同顺序获取锁可能导致死锁的场景（存在竞争）

main() {
    var data1: Int64 = 0
    var data2: Int64 = 0
    let mutex1 = Mutex()
    let mutex2 = Mutex()
    
    spawn {
        mutex1.lock()
        data1 = data1 + 1
        mutex2.lock()  // 先获取mutex1再获取mutex2
        data2 = data2 + 1
        mutex2.unlock()
        mutex1.unlock()
    }
    
    spawn {
        mutex2.lock()
        data2 = data2 + 2
        mutex1.lock()  // 先获取mutex2再获取mutex1 - 死锁风险！
        data1 = data1 + 2
        mutex1.unlock()
        mutex2.unlock()
    }
}