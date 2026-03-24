// case39: 线程池模式测试
// 测试线程池执行任务的竞争场景

class ThreadPool {
    public var taskCount: Int64 = 0
    public var completedCount: Int64 = 0
    
    public func submit(task: () -> Unit) {
        taskCount = taskCount + 1
        spawn {
            task()
            completedCount = completedCount + 1
        }
    }
}

main() {
    let pool = ThreadPool()
    var result: Int64 = 0
    
    pool.submit({
        result = result + 1
    })
    
    pool.submit({
        result = result + 2
    })
}