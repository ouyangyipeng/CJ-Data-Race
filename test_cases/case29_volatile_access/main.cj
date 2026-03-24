// case29: 多重锁保护测试（无竞争）
// 测试多个锁保护同一变量的场景

main() {
    var shared: Int64 = 0
    let mutex1 = Mutex()
    let mutex2 = Mutex()
    
    spawn {
        mutex1.lock()
        shared = shared + 1  // mutex1保护
        mutex1.unlock()
    }
    
    spawn {
        mutex2.lock()
        shared = shared + 2  // mutex2保护（不同锁，但都保护了shared）
        mutex2.unlock()
    }
}