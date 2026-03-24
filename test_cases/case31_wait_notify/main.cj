// case31: 条件变量等待通知测试
// 测试条件变量同步的场景

main() {
    var shared: Int64 = 0
    let mutex = Mutex()
    let cond = Condition()
    
    spawn {
        mutex.lock()
        while (shared == 0) {
            cond.wait(mutex)
        }
        shared = shared + 1
        mutex.unlock()
    }
    
    spawn {
        mutex.lock()
        shared = 1
        cond.notifyAll()
        mutex.unlock()
    }
}