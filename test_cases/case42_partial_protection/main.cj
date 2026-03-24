// case42: 部分保护测试
// 测试只有部分代码在锁保护内的情况（存在竞争）

main() {
    var shared: Int64 = 0
    let mutex = Mutex()
    
    spawn {
        mutex.lock()
        shared = shared + 1  // 受保护
        mutex.unlock()
        shared = shared + 2  // 未受保护！
    }
    
    spawn {
        mutex.lock()
        shared = shared + 3  // 受保护
        mutex.unlock()
    }
}